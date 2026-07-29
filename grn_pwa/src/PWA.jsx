import { FrappeApp } from 'frappe-js-sdk';
import { useEffect, useState } from 'react';
import JsBarcode from 'jsbarcode';
import './App.css';
import Button from 'react-bootstrap/Button';
import Modal from 'react-bootstrap/Modal';


var ind = 0;
const PWA = () => {
    const [items, setItems] = useState([]);
    const [currItem, setCurrentItem] = useState({});
    const [inputValue, setInputValue] = useState('');
    const [dueDate, setDueDate] = useState('');

    const [imagePreview, setImagePreview] = useState('');

    function getToken() {
        return '67b902d42ce9b93:556fa269a5af437';
    }

    const frappe = new FrappeApp('https://bee.tranqwality.com/', {
        useToken: true,
        token: getToken,
        type: 'token'
    });
    const auth = frappe.auth();
    const db = frappe.db();
    const files = frappe.file();

    const handleInputChange = (event) => {
        const { name, value } = event.target;
        setCurrentItem({ ...currItem, [name]: value });
    };

    // const handleImageChange = async (event) => {
    //     const file = event.target.files[0];
    //     const fileArgs = {
    //         /** If the file access is private then set to TRUE (optional) */
    //         "isPrivate": true,
    //         /** Folder the file exists in (optional) */
    //         "folder": "Home",
    //         /** File URL (optional) */
    //         "file_url": "",
    //         /** Doctype associated with the file (optional) */
    //         "doctype": "User",
    //         /** Docname associated with the file (mandatory if doctype is present) */
    //         "docname": "Administrator",
    //         /** Field in the document **/
    //         "fieldname": "image"
    //     }


    //     if (file) {
    //         try {
    //             const res = await files.uploadFile(
    //                 file,
    //                 fileArgs,
    //                 /** Progress Indicator callback function **/
    //                 (completedBytes, totalBytes) => console.log(Math.round((completedBytes / totalBytes) * 100), " completed")
    //             )
    //                 .then((res) => {
    //                     console.log("File Upload complete")
    //                     console.log(res)
    //                 })
    //                 .catch(e => console.error(e))
    //             console.log(res)
    //             setCurrentItem({ ...currItem, image: uploadedFile.file_url });
    //         } catch (error) {
    //             console.error('Error uploading file:', error);
    //         }
    //         const reader = new FileReader();
    //         reader.onloadend = () => {
    //             setImagePreview(reader.result);
    //         };
    //         reader.readAsDataURL(file);
    //         setCurrentItem({ ...currItem, image: file });
    //     }
    // };



    async function fetchData() {
        db.getDoc('Purchase Invoice', inputValue)
            .then((doc) => {
                if (doc?.items.length > 0) {
                    console.log(doc.items.length)
                    setImagePreview('')
                    setItems(doc?.items);
                    setCurrentItem(doc?.items[ind]);
                    setDueDate(doc?.due_date);
                }
                else {
                    handleResetValues()
                }


            })
            .catch((error) => {
                setItems([]);
                console.error(error);
            });
    }

    const [is_asin, setIssAsin] = useState(0)
    const submitForm = (e) => {

        e.preventDefault();
        let index = 0;
        auth
            .loginWithUsernamePassword({ username: 'Administrator', password: 'admin' })
            .then((response) => console.log('Logged in'))
            .catch((error) => console.error(error));

        db.getDoc('Purchase Invoice', inputValue)
            .then((doc) => {
                setImagePreview('')
                console.log(doc)
                setIssAsin(doc?.custom_is_asin)
                setItems(doc?.items);
                setCurrentItem(doc?.items[ind]);
                setDueDate(doc?.due_date);
                // ind = 0
            })
            .catch((error) => {
                setItems([]);
                console.error(error);
            });
    };

    const toggleAdditionalField = () => {
        // Your toggle logic here
    };

    const previous = () => {

        if (ind === 0) {
            alert('No previous element');
        } else {
            setCurrentItem(items[ind - 1]);
            // saveData();
            ind = ind - 1
        }
    };

    const next = () => {

        if (ind === items.length - 1) {
            alert('No next element');
        } else {
            setCurrentItem(items[ind + 1]);
            // saveData();
            ind = ind + 1
        }
    };

    const saveData = () => {
        if (!currItem.custom_is_asin) {
            const currentItemCode = currItem.item_code

            // console.log(currentItemCode)

            db.updateDoc('Item', currentItemCode, {
                brand: currItem.brand,
                custom_mrp: currItem.custom_mrp,
                ean: currItem.custom_ean || currItem.ean,
                custom_sub_category: currItem.custom_subcategory,
                description: currItem.description,

            })
                .then((doc) => {
                    console.log(doc)
                    PurchaseUpdateDocInvoice()
                })
                .catch((error) => console.error(error));
        }
        else {
            PurchaseUpdateDocInvoice()
        }
    };



    async function PurchaseUpdateDocInvoice() {
        const updatedItems = items.map((item) => {
            if (item.name === currItem.name) {
                console.log(item, "ittteeemmmmm")
                return {
                    ...item,
                    custom_asin: currItem.custom_asin,
                    custom_box_number: currItem.custom_box_number,
                    // item_name: currItem.item_name,
                    // description: currItem.description,
                    // brand: currItem.brand,
                    // custom_subcategory: currItem.custom_subcategory,
                    // custom_ean: currItem.custom_ean,
                    // custom_mrp: currItem.custom_mrp,
                    qty: parseFloat(currItem.qty),
                    rejected_qty: parseFloat(currItem.received_qty) - parseFloat(currItem.qty),
                    // received_qty: currItem.received_qty
                    // Add more properties as needed
                };
            }
            return item; // Return the original item if it doesn't match the criteria
        });


        db.updateDoc('Purchase Invoice', inputValue, {
            items: updatedItems,
            due_date: dueDate
        })
            .then((doc) => {
                // setInputValue('');
                // setCurrentItem({
                //     custom_asin: '',
                //     custom_box_number: '',
                //     image: '',
                //     item_name: '',
                //     description: '',
                //     brand: '',
                //     custom_subcategory: '',
                //     custom_ean: '',
                //     custom_mrp: '',
                //     qty: '',
                //     received_qty: '',

                // });
                // setDueDate('');
                // setItems([]);
                // ind = 0
                setCurrentItem(items[ind]);
                alert("Updated Successfully")
                fetchData()
                console.log(doc);
            })
            .catch((error) => {
                try {
                    console.log(error)

                    const errorObject = JSON.parse(error?._server_messages);
                    const error_message = errorObject[0];
                    console.log(JSON.parse(error_message?.message));
                    alert(JSON.parse(error_message.message));

                } catch (error) {
                    alert('Check The Details Again');
                }
            });
    }

    const printBarcode = () => {
        const barcodeWindow = window.open('');
        barcodeWindow.document.write('<svg id="barcode"></svg>');

        JsBarcode(barcodeWindow.document.getElementById('barcode'), currItem?.item_code, {
            height: 50,
            text: currItem?.rate,
            displayValue: true
        });

        barcodeWindow.print();
        barcodeWindow.close();
    };

    const [modalShow, setModalShow] = useState(false);
    const [qcModal, setQcModal] = useState(false);
    useEffect(() => {
        auth
            .loginWithUsernamePassword({ username: 'Administrator', password: 'admin' })
            .then((response) => console.log('Logged in'))
            .catch((error) => console.error(error));

        getBrandList()
        getInvoiceList()

    }, [])




    const [brandList, setBrandList] = useState([])

    async function getBrandList() {
        db.getDocList('Brand', {
            fields: ['name', 'creation'],
            limit: 700,
            /** Sort results by field and order  */
            orderBy: {
                field: 'creation',
                order: 'desc',
            },
        })
            .then((docs) => {
                // console.log(docs)
                setBrandList(docs)
            })
            .catch((error) => console.error(error));
    }

    async function addNewBrand(b) {

        // console.log(b)
        setSelectedBrand(b)
        db.createDoc('Brand', {
            brand: b,
        })
            .then((doc) => {
                // console.log(doc)
                getBrandList()
                setCurrentItem({ ...currItem, brand: b });
                setModalShow(false)
            })
            .catch((error) => console.error(error));
    }


    const [invoiceList, setInvoiceList] = useState([])
    async function getInvoiceList() {

        db.getDocList('Purchase Invoice', {
            /** Fields to be fetched */
            fields: ['name', 'creation'],
            /** Filters to be applied - SQL AND operation */
            filters: [['docstatus', '=', '0']],

            limit: 50,
            /** Sort results by field and order  */
            orderBy: {
                field: 'creation',
                order: 'desc',
            },


        })
            .then((docs) => {
                setInvoiceList(docs)
            })
            .catch((error) => console.error(error));
    }




    // qc conditions based 

    const [qcItem, setQcItem] = useState({
        purchase_invoice: '',
        item_code: '',
        damaged: 1,
        main_damaged: 0,
        hole_main: 1,
        torn_main: 0,
        marks_main: 0,
        scratched_main: 0,
        part_damaged: 0,
        hole_part: 0,
        torn_part: 0,
        marks_part: 0,
        scratched_part: 0,
        short: 0,
        main_short: 0,
        part_short: '',
        received: 0,
        out_of: 0,
        importance: '',
        not_working: 0,
        offer_discount: '',
        buy_part: 0,
        repair: 0,
        scrap: 0,
        qc_pass: '',
    })

    const updateQC = (e) => {
        e.preventDefault()
        db.createDoc('Quality Checks', { ...qcItem, purchase_invoice: inputValue, item_code: currItem.item_code })
            .then((doc) => {
                console.log(doc)
                setQcModal(false)
                fetchData()
                setQcItem({
                    purchase_invoice: '',
                    item_code: '',
                    damaged: 1,
                    main_damaged: 0,
                    hole_main: 1,
                    torn_main: 0,
                    marks_main: 0,
                    scratched_main: 0,
                    part_damaged: 0,
                    hole_part: 0,
                    torn_part: 0,
                    marks_part: 0,
                    scratched_part: 0,
                    short: 0,
                    main_short: 0,
                    part_short: '',
                    received: 0,
                    out_of: 0,
                    importance: '',
                    not_working: 0,
                    offer_discount: '',
                    buy_part: 0,
                    repair: 0,
                    scrap: 0,
                    qc_pass: '',
                })
            })
            .catch((error) => console.error(error));
    }


    const handleQcUpdate = (event) => {
        const { name, checked, type, value } = event.target;

        if (type == 'checkbox') {

            setQcItem({ ...qcItem, [name]: checked });
        }
        else {
            setQcItem({ ...qcItem, [name]: value });

        }
    }


    const [selectedConditions, setSelectedConditions] = useState([]);
    // const handleConditionChange = (optionId) => {
    //     if (selectedConditions.includes(optionId)) {

    //         setSelectedConditions(selectedConditions.filter((item) => item !== optionId));
    //     } else {

    //         setSelectedConditions([...selectedConditions, optionId]);
    //     }
    // };


    const handleSelectChange = (e) => {
        const selectedBrand = e.target.value;
        setCurrentItem({ ...currItem, brand: selectedBrand });

    };

    const [rotationAngle, setRotationAngle] = useState(0);

    const handleRotation = () => {
        handleResetValues()
        setRotationAngle(350);
    };


    function handleResetValues() {
        setInputValue('');
        setCurrentItem({
            custom_asin: '',
            custom_box_number: '',
            image: '',
            item_name: '',
            description: '',
            brand: '',
            custom_subcategory: '',
            custom_ean: '',
            custom_mrp: '',
            qty: '',
            received_qty: '',

        });
        setDueDate('');
        setItems([]);
        ind = 0
    }

    const [selectedBrand, setSelectedBrand] = useState('')

    const [brandValue, setBrandValue] = useState('')

    return (
        <>
            <form onSubmit={submitForm}>
                <div className="search-container container-1">





                    <div className='search-btn-container'>
                        <div className='left-btn' onClick={submitForm}>
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-search" viewBox="0 0 16 16">
                                <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001q.044.06.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1 1 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0" />
                            </svg>
                        </div>
                        <input class="form-control" list="datalistOptions" id="exampleDataList" placeholder="Search search..." value={inputValue} onChange={(e) => {
                            setInputValue(e.target.value)
                        }} />
                        <div className='left-btn' onClick={handleRotation}>
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                width="16"
                                height="16"
                                fill="currentColor"
                                className="bi bi-arrow-clockwise"
                                viewBox="0 0 16 16"
                                style={{ transform: `rotate(${rotationAngle}deg)`, transition: 'all ease 1s' }}
                            >
                                <path
                                    fillRule="evenodd"
                                    d="M8 3a5 5 0 1 0 4.546 2.914.5.5 0 0 1 .908-.417A6 6 0 1 1 8 2z"
                                />
                                <path
                                    d="M8 4.466V.534a.25.25 0 0 1 .41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 0 1 8 4.466"
                                />
                            </svg>
                        </div>
                    </div>
                    <datalist id="datalistOptions" onChange={() => {
                        submitForm(e)
                    }}>
                        {
                            invoiceList.length > 0 && invoiceList.map((invoice, index) => {
                                return (
                                    <option value={invoice?.name} >{invoice?.name}</option>
                                )
                            })
                        }

                    </datalist>


                </div>
            </form>
            <form>

                <div className="search-container">
                    <h5 style={{ fontSize: '1rem', textAlign: 'center', fontWeight: 600, color: 'grey' }}> {ind + 1} of {items.length}</h5>


                    {is_asin == 1 && (
                        <div id="boxNumberField">
                            <label htmlFor="asinReason">Box Number:</label>
                            <input type="text" id="asinReason" name="custom_box_number" value={currItem?.custom_box_number} onChange={handleInputChange} />
                        </div>
                    )}
                    <br />
                    {is_asin == 1 &&
                        <>
                            <label htmlFor="itemName">ASIN Number:</label>
                            <input type="text" id="custom_asin" value={currItem?.custom_asin || ''} name="custom_asin" placeholder="ASIN Number" onChange={handleInputChange} />
                            <br />
                            <br />
                        </>
                    }



                    {currItem?.image &&
                        <><div>

                            <img src={currItem?.image} alt="Preview" style={{ maxWidth: '300px', width: '100%', height: '200px' }} />
                        </div>
                            <br />
                            <br />
                        </>
                    }



                    <label>Item Code :</label>
                    <input type="text" id="item_name" placeholder="ItemName" value={currItem?.item_code} disabled />
                    <label>ItemName :</label>
                    <input type="text" id="item_name" name="item_name" placeholder="ItemName" value={currItem?.item_name} onChange={handleInputChange} />

                    <label>Description :</label>
                    <input type="text" id="description" name="description" placeholder="Description" value={currItem?.description} onChange={handleInputChange} />
                    <Modal
                        show={modalShow}

                        size="md"
                        aria-labelledby="contained-modal-title-vcenter"
                        centered
                    >
                        <Modal.Header >
                            <Modal.Title id="contained-modal-title-vcenter">
                                Create a New Brand
                            </Modal.Title>
                        </Modal.Header>
                        <Modal.Body>

                            <input value={selectedBrand} onChange={(e) => {
                                setSelectedBrand(e.target.value)
                            }} />

                        </Modal.Body>
                        <Modal.Footer>
                            <Button onClick={() => {
                                addNewBrand(selectedBrand)

                            }}>Add</Button>
                            <Button onClick={() => setModalShow(false)}>Close</Button>

                        </Modal.Footer>

                    </Modal>

                    <label>Brand :</label>
                    <input
                        className="form-control"
                        list="brandOptions"
                        id="brandInput"
                        placeholder="Search and Select brand..."
                        value={currItem?.brand || ''}
                        onChange={(e) => {

                            if (e.target.value == 'Create a New Brand') {
                                setModalShow(e.target.value)
                                setBrandValue('')
                            }
                            else {
                                handleSelectChange(e)
                                setBrandValue(e.target.value)
                            }

                        }}
                    />

                    <datalist id="brandOptions" defaultValue={currItem?.brand} onChange={handleSelectChange}>
                        <option defaultValue='New_value@#!@#$#@!@#$'>
                            Create a New Brand
                        </option>
                        {brandList.map((brand, index) => (
                            <option
                                key={index}
                                defaultValue={brand?.name?.toLowerCase()}
                                selected={currItem?.brand?.toLowerCase() === brand?.value?.toLowerCase() ? true : false}
                            >
                                {brand.name}
                            </option>
                        ))}
                    </datalist>

                    <br />




                    <label>Sub-Category</label>
                    <input type="text" id="subcategory" name="custom_subcategory" value={currItem?.custom_subcategory} onChange={handleInputChange} />
                    <div className="container">
                        <div className="field">
                            <label>EAN</label>
                            <input type="number" id="ean" name="ean" value={currItem?.custom_ean || currItem?.ean || ''} onChange={handleInputChange} />
                        </div>
                        <div className="field">
                            <label>MRP:</label>
                            <input type="number" id="rate" name="custom_mrp" value={currItem?.custom_mrp} onChange={handleInputChange} />
                        </div>
                    </div>
                    <div className="container">
                        <div className="field">
                            <label htmlFor="field2">Received Qty :</label>
                            <input type="number" id="qty" name="qty" value={currItem?.qty} disabled onChange={handleInputChange} />
                        </div>
                        <div className="field">
                            <label htmlFor="field1">Accepted Qty:</label>
                            <input type="number" id="received_qty" name="received_qty" defaultValue={currItem?.received_qty} onChange={handleInputChange} />
                        </div>

                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div className='left-btn' onClick={() => {
                            setQcModal(true)
                        }} style={{ width: '40px' }}>
                            <button style={{ padding: '5px', marginTop: '10px' }} type='button'>QC</button>
                        </div>
                        <label htmlFor="qc"> QC Pass: {currItem?.custom_qc_pass}</label>

                    </div>



                    <Modal
                        show={qcModal}

                        size="lg"
                        aria-labelledby="contained-modal-title-vcenter"
                        centered
                    >
                        <Modal.Header >
                            <Modal.Title id="contained-modal-title-vcenter">
                                QC
                            </Modal.Title>
                        </Modal.Header>
                        <Modal.Body>
                            <div className="container row ">
                                <form onSubmit={updateQC}>

                                    <div className=" m-1 col-12">
                                        <label htmlFor="item_name" className="form-label-1">Purchase Invoice:</label>
                                        <input
                                            type="text"
                                            className="form-control"
                                            id="item_name"
                                            name="item_name"

                                            value={inputValue}

                                            disabled
                                        />
                                    </div>
                                    <div className="m-1 col-12">
                                        <label htmlFor="description" className="form-label-1">Item Code</label>
                                        <input
                                            type="text"
                                            className="form-control"
                                            id="description"
                                            name="description"
                                            // placeholder=""
                                            value={currItem?.item_code}
                                            disabled
                                        />
                                    </div>
                                    <div className="m-1 col-12">
                                        <label htmlFor="description" className="form-label-1">Product Condition</label>
                                        <div className="form-check">
                                            <input
                                                type="checkbox"
                                                className="form-check-input"
                                                id="productCondition"
                                                name="damaged"
                                                defaultChecked={currItem?.damaged}

                                            />
                                            <label className="form-check-label" htmlFor="productCondition">Damaged</label>
                                        </div>

                                    </div>
                                    <div className="mt-2 form-check col-6" style={{ marginLeft: '20px' }}>
                                        <div>
                                            <input
                                                type="checkbox"
                                                className="form-check-input"
                                                name='main_product'
                                                defaultChecked={qcItem.main_product}
                                                onChange={handleQcUpdate}
                                            />
                                            <label className="form-check-label" htmlFor='main_product'>Main Product</label>
                                        </div>
                                        {qcItem.main_product && <>
                                            <div className="mt-2 form-check col-3" style={{ marginLeft: '0px' }}>
                                                <input
                                                    type="checkbox"
                                                    className="form-check-input"
                                                    name='hole_main'
                                                    defaultChecked={qcItem.hole_main}
                                                    onChange={handleQcUpdate}
                                                />
                                                <label className="form-check-label" htmlFor='hole_main'>Hole</label>
                                            </div>

                                            <div className="mt-2 form-check col-3" style={{ marginLeft: '0px' }}>
                                                <input
                                                    type="checkbox"
                                                    className="form-check-input"
                                                    name='marks_main'
                                                    checked={qcItem.marks_main}
                                                    onChange={handleQcUpdate}
                                                />
                                                <label className="form-check-label" htmlFor='marks_main'>Marks </label>
                                            </div>
                                            <div className="mt-2 form-check col-3" style={{ marginLeft: '0px' }}>
                                                <input
                                                    type="checkbox"
                                                    className="form-check-input"
                                                    name='torn_main'
                                                    checked={qcItem.torn_main}
                                                    onChange={handleQcUpdate}
                                                />
                                                <label className="form-check-label" htmlFor='torn_main'>Torn </label>
                                            </div>

                                            <div className="mt-2 form-check col-3" style={{ marginLeft: '0px' }}>
                                                <input
                                                    type="checkbox"
                                                    className="form-check-input"
                                                    name='scratched_main'
                                                    checked={qcItem.scratched_main}
                                                    onChange={handleQcUpdate}
                                                />
                                                <label className="form-check-label" htmlFor='scratched_main'>Scratch</label>
                                            </div>
                                        </>}
                                    </div>


                                    {/* part strat here*/}
                                    <div className="mt-2 form-check col-3" style={{ marginLeft: '20px' }}>
                                        <input
                                            type="checkbox"
                                            className="form-check-input"
                                            name='part_damaged'
                                            defaultChecked={qcItem.part_damaged}
                                            onChange={handleQcUpdate}
                                        />
                                        <label className="form-check-label" htmlFor='part_damaged'>Part</label>

                                        {qcItem.part_damaged == 1 && <>
                                            <div className="mt-2 form-check col-3" style={{ marginLeft: '0px' }}>
                                                <input
                                                    type="checkbox"
                                                    className="form-check-input"
                                                    name='hole_part'
                                                    defaultChecked={qcItem.hole_part}
                                                    onChange={handleQcUpdate}
                                                />
                                                <label className="form-check-label" htmlFor='hole_part'>Hole</label>
                                            </div>

                                            <div className="mt-2 form-check col-3" style={{ marginLeft: '0px' }}>
                                                <input
                                                    type="checkbox"
                                                    className="form-check-input"
                                                    name='marks_part'
                                                    checked={qcItem.marks_part}
                                                    onChange={handleQcUpdate}
                                                />
                                                <label className="form-check-label" htmlFor='marks_part'>Marks </label>
                                            </div>
                                            <div className="mt-2 form-check col-3" style={{ marginLeft: '0px' }}>
                                                <input
                                                    type="checkbox"
                                                    className="form-check-input"
                                                    name='torn_part'
                                                    checked={qcItem.torn_part}
                                                    onChange={handleQcUpdate}
                                                />
                                                <label className="form-check-label" htmlFor='torn_part'>Torn </label>
                                            </div>

                                            <div className="mt-2 form-check col-3" style={{ marginLeft: '0px' }}>
                                                <input
                                                    type="checkbox"
                                                    className="form-check-input"
                                                    name='scratched_part'
                                                    checked={qcItem.scratched_part}
                                                    onChange={handleQcUpdate}
                                                />
                                                <label className="form-check-label" htmlFor='scratched_part'>Scratch</label>
                                            </div>
                                        </>}
                                    </div>



                                    <div className="mt-2 form-check col-10" style={{ marginLeft: '20px' }}>
                                        <input
                                            type="checkbox"
                                            className="form-check-input"
                                            name='short'
                                            checked={qcItem.short}
                                            onChange={handleQcUpdate}
                                        />
                                        <label className="form-check-label" htmlFor='short'>Short</label>
                                    </div>
                                    <div className="mt-2 form-check col-5" style={{ marginLeft: '20px' }}>
                                        <input
                                            type="checkbox"
                                            className="form-check-input"
                                            name='main_short'
                                            checked={qcItem.main_short}
                                            onChange={handleQcUpdate}
                                        />
                                        <label className="form-check-label" htmlFor='main_short'>Main</label>
                                    </div>
                                    <div className="mt-2 form-check col-12" >
                                        <label className="form-check-label" htmlFor='part' style={{ marginBottom: '10px' }}>Part</label>
                                        <input
                                            type="text"
                                            className="form-control"
                                            name='part_short'
                                            value={qcItem.part_short}
                                            onChange={handleQcUpdate}
                                        />

                                    </div>
                                    <div className="mt-2 form-check col-12" >
                                        <label className="form-check-label" htmlFor='received' style={{ marginBottom: '10px' }}>Received</label>
                                        <input
                                            type="number"
                                            className="form-control"
                                            name='received'
                                            value={qcItem.received}
                                            onChange={handleQcUpdate}
                                        />
                                    </div>
                                    <div className="mt-2 form-check col-12 mt-2" >
                                        <label className="form-check-label" htmlFor='out_of' style={{ marginBottom: '10px' }}
                                        >Out Of</label>
                                        <input
                                            type="number"
                                            className="form-control"
                                            name='out_of'
                                            value={qcItem.out_of}
                                            onChange={handleQcUpdate}
                                        />
                                    </div>
                                    <div className="mt-2 form-check col-12" >
                                        <label className="form-check-label" htmlFor='importance' style={{ marginBottom: '10px' }}
                                        >Importance :</label>
                                        <select
                                            className="form-select"
                                            defaultValue={qcItem.importance}
                                            onChange={handleQcUpdate}
                                        >
                                            <option value="">Select an option</option>
                                            <option value="Low">Low</option>

                                            <option value="High">High</option>
                                            {/* Add more options as needed */}
                                        </select>
                                    </div>
                                    <div className="mt-2 form-check col-12 p-3" style={{ marginLeft: '20px' }}>
                                        <input
                                            type="checkbox"
                                            className="form-check-input"
                                            name='not_working'
                                            checked={qcItem.not_working}
                                            onChange={handleQcUpdate}
                                        />
                                        <label className="form-check-label" htmlFor='not_working'>Not Working</label>
                                    </div>

                                    <div>
                                        <label className="form-check-label" htmlFor='offer_discount' style={{ marginBottom: '10px' }}
                                        >Offer Discount :</label>
                                        <select
                                            className="form-select"
                                            defaultValue={qcItem.offer_discount}
                                            onChange={handleQcUpdate}
                                        >
                                            <option value="">Select an option</option>
                                            <option value="25">25</option>

                                            <option value="50">50</option>
                                            {/* Add more options as needed */}
                                        </select>
                                    </div>


                                    <div className="mt-2 form-check col-10" style={{ marginLeft: '20px' }}>
                                        <input
                                            type="checkbox"
                                            className="form-check-input"
                                            name='buy_part'
                                            checked={qcItem.buy_part}
                                            onChange={handleQcUpdate}
                                        />
                                        <label className="form-check-label" htmlFor='buy_part'>Buy Part</label>
                                    </div>
                                    <div className="mt-2 form-check col-10" style={{ marginLeft: '20px' }}>
                                        <input
                                            type="checkbox"
                                            className="form-check-input"
                                            name='repair'
                                            checked={qcItem.repair}
                                            onChange={handleQcUpdate}
                                        />
                                        <label className="form-check-label" htmlFor='repair'>Repair</label>
                                    </div>
                                    <div className="mt-2 form-check col-10" style={{ marginLeft: '20px' }}>
                                        <input
                                            type="checkbox"
                                            className="form-check-input"
                                            name='scrap'
                                            checked={qcItem.scrap}
                                            onChange={handleQcUpdate}
                                        />
                                        <label className="form-check-label" htmlFor='scrap'>Scrap</label>
                                    </div>
                                    <div className="mt-2 form-check col-12" >
                                        <label className="form-check-label" htmlFor='qc_pass' style={{ marginBottom: '10px' }}
                                        >QC Pass :</label>
                                        <select
                                            className="form-select"
                                            defaultValue={qcItem.qc_pass}
                                            name='qc_pass'
                                            onChange={handleQcUpdate}
                                            required
                                        >
                                            <option value="">Select</option>
                                            <option value="Yes">Yes</option>

                                            <option value="No">No</option>

                                        </select>
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '20px', marginBlock: '30px', }}>
                                        <Button
                                            type='submit'
                                        >Submit</Button>
                                        <Button onClick={() => setQcModal(false)} >Close</Button>
                                    </div>
                                </form>
                            </div>
                        </Modal.Body>
                    </Modal>
                    <div id="additionalField" style={{ display: 'none' }}>
                        <label htmlFor="additionalInfo">Reason:</label>
                        <input type="text" id="additionalInfo" name="additionalInfo" />
                        <br />
                    </div>
                    <br />
                </div>
                <div className="search-container">
                    <div className='save-container'>
                        <div className='left-btn' onClick={previous}>
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-arrow-left-square" viewBox="0 0 16 16">
                                <path fill-rule="evenodd" d="M15 2a1 1 0 0 0-1-1H2a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1zM0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2zm11.5 5.5a.5.5 0 0 1 0 1H5.707l2.147 2.146a.5.5 0 0 1-.708.708l-3-3a.5.5 0 0 1 0-.708l3-3a.5.5 0 1 1 .708.708L5.707 7.5z" />
                            </svg>
                        </div>
                        <button type="button" className='save-btn' onClick={saveData}>
                            Save Data
                        </button>
                        <div className='right-btn' onClick={next}>
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-arrow-right-square" viewBox="0 0 16 16">
                                <path fill-rule="evenodd" d="M15 2a1 1 0 0 0-1-1H2a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1zM0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2zm4.5 5.5a.5.5 0 0 0 0 1h5.793l-2.147 2.146a.5.5 0 0 0 .708.708l3-3a.5.5 0 0 0 0-.708l-3-3a.5.5 0 1 0-.708.708L10.293 7.5z" />
                            </svg>
                        </div>
                    </div>
                    <button type="button" onClick={printBarcode}>
                        Print barcode
                    </button>
                </div>
            </form >
        </>
    );
};

export default PWA;


// <br />
// <br />
// <input type="file" id="image" name="image" />


// <div className='card-container'>
//     <select className="form-select" ariaLabel="" defaultValue={inputValue} onChange={(e) => {
//         console.log(e.target.value)
//         setInputValue(e.target.value)
//         submitForm(e)

//     }}>
// <label htmlFor="asinSelect" className='mb-2'>Type : {is_asin == 0 ? "ASIN" : "Non-Asin"}</label>


//         <option value="">Select an invoice...</option>



//     </select>
// </div>
// <option value="">Select QC Pass</option>


// <select className="form-select" ariaLabel="" defaultValue={currItem.brand} onChange={(e) => {
//     if (e.target.value == 'new_value@#!@#$#@!@#$') {
//         setModalShow(true)
//     }
//     else {
//         setCurrentItem({ ...currItem, brand: e.target.value });
//     }
// }}>
//     <option value='new_value@#!@#$#@!@#$'>
//         Create a New Brand
//     </option>

//     {
//         brandList.length > 0 && brandList.map((brand, index) => {
//             return (
//                 <option value={brand?.name?.toLowerCase()} selected={currItem?.brand?.toLowerCase() == brand?.name?.toLowerCase() ? true : false}>{brand?.name}</option>
//             )
//         })
//     }


// </select>


// <select id="asinSelect" name="productType" value={currItem?.custom_is_asin} onChange={handleInputChange}>
// <option value=''>Select</option>
// <option value={0}>ASIN</option>
// <option value={1}>Non-ASIN</option>
// </select>


// <div className="mt-2 form-check col-3" style={{ marginLeft: '20px' }}>
// <input
//     type="checkbox"
//     className="form-check-input"
//     name='torn'
//     checked={qcItem.torn}
//     onChange={handleQcUpdate}
// />
// <label className="form-check-label" htmlFor='torn'>torn</label>
// </div>

// <select id="qc" name="qc" onChange={(e) => {
//     // console.log(e.target.value)
//     if (e.target.value == 0) {
//         setQcModal(true)
//     }
//     else {
//         setQcModal(false)
//     }
// }}>
//     <option value={1}>Yes</option>
//     <option value={0}>No</option>
// </select>