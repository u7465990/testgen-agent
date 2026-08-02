package com.demo;

import com.demo.BankAccount;
import org.junit.Assert;
import org.junit.Test;

public class BankAccount_getOwner_Test_Normal_2 {


    @Test
    public void testGetOwnerReturnsTypicalOwnerName() {
        BankAccount account = new BankAccount("Alice", 1000.0);
        Assert.assertEquals("Alice", account.getOwner());
    }

}
